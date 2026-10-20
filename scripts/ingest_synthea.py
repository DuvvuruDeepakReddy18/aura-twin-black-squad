"""Import a small, traceable subset of the official Synthea sample CSV archive.

The archive remains outside published artifacts. No names, addresses, contact
details, raw source UUIDs or fabricated measurements enter the exported subset.
Synthetic context is arbitrarily paired with research participants, never linked.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = '2c7d489eb4c8bc967dbfab3499a0f573818880dc'
SOURCE_URL = ('https://raw.githubusercontent.com/synthetichealth/synthea-sample-data/'
              f'{SOURCE_COMMIT}/downloads/latest/synthea_sample_data_csv_latest.zip')
SOURCE_SHA256 = 'a7f6f24d3ebd96bbf0b5ef29a16ca6bd6d7ca68db65537ca6ccab6adc20ec609'
SOURCE_PAGE = 'https://synthetichealth.github.io/downloads.html'
DICTIONARY = 'https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary'
FIELDS = {'bmi': '39156-5', 'hba1c': '4548-4', 'ldl': '18262-6'}
VERSION = 'aura-synthea-import-1.0.0'


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parsed_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def completed_years(born: date, at: date) -> int:
    return at.year - born.year - ((at.month, at.day) < (born.month, born.day))


def read_table(archive: zipfile.ZipFile, name: str):
    data = archive.read(name)
    rows = []
    for line, row in enumerate(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))), 2):
        normalized = {key.upper(): value for key, value in row.items()}
        normalized['_ROW'] = line
        rows.append(normalized)
    return rows, {'file': name, 'sha256': sha256(data), 'bytes': len(data), 'rows': len(rows)}


def observation(row):
    value = row['VALUE']
    if row.get('TYPE') == 'numeric':
        try:
            value = float(value)
        except ValueError:
            return None
        if not (-float('inf') < value < float('inf')):
            return None
    return {'observedAt': row['DATE'], 'code': row['CODE'], 'description': row['DESCRIPTION'],
            'value': value, 'unit': row.get('UNITS') or None, 'type': row.get('TYPE'),
            'source': 'synthetic_ehr', 'sourceTable': 'observations.csv', 'sourceRow': row['_ROW']}


def historical_row(row, table, as_of):
    stop = parsed_date(row.get('STOP', ''))
    # Do not reveal a resolution/discontinuation date which occurs after the snapshot.
    return {'code': row['CODE'], 'description': row['DESCRIPTION'], 'start': row['START'],
            'stop': row.get('STOP') if stop and stop <= as_of else None,
            'statusAtSnapshot': 'ended' if stop and stop <= as_of else 'active',
            'source': 'synthetic_ehr', 'sourceTable': table, 'sourceRow': row['_ROW']}


def build(archive_path: Path, output_dir: Path, as_of: date, count=16,
          expected_sha=SOURCE_SHA256, participant_ids=None):
    raw = archive_path.read_bytes()
    actual_sha = sha256(raw)
    if actual_sha != expected_sha:
        raise ValueError(f'Source archive SHA-256 mismatch: expected {expected_sha}; got {actual_sha}.')
    tables, file_info, zip_dates = {}, [], {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in ['patients.csv', 'observations.csv', 'conditions.csv', 'medications.csv']:
            tables[name], info = read_table(archive, name)
            file_info.append(info)
            zip_dates[name] = list(archive.getinfo(name).date_time)

    candidates, exclusions = [], {'invalidBirthDate': 0, 'under18AtSnapshot': 0,
                                 'notAliveAtSnapshot': 0, 'bornAfterSnapshot': 0}
    for row in tables['patients.csv']:
        born = parsed_date(row['BIRTHDATE'])
        death = parsed_date(row.get('DEATHDATE', ''))
        if born is None:
            exclusions['invalidBirthDate'] += 1
        elif born > as_of:
            exclusions['bornAfterSnapshot'] += 1
        elif completed_years(born, as_of) < 18:
            exclusions['under18AtSnapshot'] += 1
        elif death and death <= as_of:
            exclusions['notAliveAtSnapshot'] += 1
        else:
            candidates.append(row)
    candidates.sort(key=lambda row: row['ID'])
    if len(candidates) < count:
        raise ValueError(f'Only {len(candidates)} eligible profiles; {count} requested.')
    chosen = candidates[:count]
    ids = {row['ID'] for row in chosen}
    indexed = {name: {key: [] for key in ids} for name in tables if name != 'patients.csv'}
    quality = {}
    for name, by_id in indexed.items():
        timestamp_key = 'DATE' if name == 'observations.csv' else 'START'
        report = {'sourceRows': len(tables[name]), 'selectedProfileRows': 0,
                  'invalidDateRows': 0, 'afterSnapshotRows': 0, 'usableRows': 0}
        for row in tables[name]:
            if row['PATIENT'] not in ids:
                continue
            report['selectedProfileRows'] += 1
            recorded = parsed_date(row[timestamp_key])
            if recorded is None:
                report['invalidDateRows'] += 1
            elif recorded > as_of:
                report['afterSnapshotRows'] += 1
            else:
                by_id[row['PATIENT']].append(row)
                report['usableRows'] += 1
        quality[name] = report

    profiles, assignments = [], []
    participant_ids = participant_ids or [f'{i:03d}' for i in range(1, count + 1)]
    if len(participant_ids) != count or len(set(participant_ids)) != count:
        raise ValueError('Provide exactly one unique participant identifier per selected profile.')
    for position, patient in enumerate(chosen, 1):
        identifier = patient['ID']
        profile_id = f'SYN-EHR-{position:03d}'
        source_hash = sha256(identifier.encode('utf-8'))
        age = completed_years(parsed_date(patient['BIRTHDATE']), as_of)
        observations = [observation(row) for row in sorted(indexed['observations.csv'][identifier],
                                                         key=lambda row: (row['DATE'], row['_ROW']))]
        invalid_numeric = sum(row is None for row in observations)
        observations = [row for row in observations if row is not None]
        provenance = {
            'age': {'source': 'synthetic_ehr', 'sourceTable': 'patients.csv',
                    'sourceRow': patient['_ROW'], 'derived': True,
                    'method': 'Completed years from source BIRTHDATE to the declared snapshot date.',
                    'snapshotAt': as_of.isoformat()},
            'sex': {'source': 'synthetic_ehr', 'sourceTable': 'patients.csv',
                    'sourceRow': patient['_ROW'], 'sourceField': 'GENDER'},
        }
        scalar = {}
        for key, code in FIELDS.items():
            found = [row for row in observations if row['code'] == code and isinstance(row['value'], (int, float))]
            latest = found[-1] if found else None
            scalar[key] = latest['value'] if latest else None
            provenance[key] = latest or {'source': 'synthetic_ehr', 'status': 'unavailable',
                                        'reason': f'No numeric source observation for LOINC {code} by snapshot.'}
        diagnoses = [historical_row(row, 'conditions.csv', as_of) for row in
                     sorted(indexed['conditions.csv'][identifier], key=lambda row: (row['START'], row['_ROW']))]
        medications = [historical_row(row, 'medications.csv', as_of) for row in
                       sorted(indexed['medications.csv'][identifier], key=lambda row: (row['START'], row['_ROW']))]
        profile = {'id': profile_id, 'sourcePatientSHA256': source_hash,
                   'snapshotAt': as_of.isoformat(), 'age': age, 'sex': patient['GENDER'],
                   **scalar, 'fieldProvenance': provenance, 'diagnoses': diagnoses[-30:],
                   'medications': medications[-30:], 'observations': observations[-40:],
                   'geneticContext': None,
                   'geneticContextStatus': 'Unavailable in this imported Synthea subset.',
                   'exportSummary': {'observationsAvailable': len(observations),
                                     'observationsExported': min(40, len(observations)),
                                     'invalidNumericObservations': invalid_numeric,
                                     'diagnosesAvailable': len(diagnoses),
                                     'diagnosesExported': min(30, len(diagnoses)),
                                     'medicationsAvailable': len(medications),
                                     'medicationsExported': min(30, len(medications))}}
        profiles.append(profile)
        assignments.append({'researchParticipantId': participant_ids[position - 1],
                            'syntheticProfileId': profile_id, 'sourcePatientSHA256': source_hash})

    source = {'name': 'Synthea official sample CSV', 'kind': 'synthetic_ehr',
              'version': f'official-sample-{SOURCE_COMMIT[:12]}', 'sourceCommit': SOURCE_COMMIT,
              'sourcePage': SOURCE_PAGE, 'downloadUrl': SOURCE_URL, 'archiveSHA256': actual_sha,
              'archiveBytes': len(raw), 'generatorVersion': None, 'generatorSeed': None,
              'versionNote': 'Generator version/seed were not supplied in this CSV archive; not inferred.',
              'license': 'Official sample-data terms permit unrestricted use; separate from application MIT license.',
              'licenseUrl': SOURCE_PAGE, 'citationDOI': '10.1093/jamia/ocx079',
              'dataDictionary': DICTIONARY, 'archiveEntryLocalDateComponents': zip_dates,
              'snapshotAt': as_of.isoformat(),
              'snapshotNote': 'Chosen historical cutoff, not an asserted source generation date.',
              'preprocessingVersion': VERSION}
    payload = {'schemaVersion': 1, 'source': source, 'profiles': profiles}
    manifest = {'schemaVersion': 1, 'preprocessingVersion': VERSION, 'source': source,
                'retrievedOn': datetime.now(timezone.utc).date().isoformat(), 'files': file_info,
                'selection': {'sourcePatients': len(tables['patients.csv']), 'eligibleAdults': len(candidates),
                              'selectedProfiles': count, 'exclusions': exclusions,
                              'rule': 'Alive adults at the declared snapshot; ascending source UUID, first N.',
                              'targetOrWearableDrivenSelection': False},
                'validation': quality,
                'retention': 'Last 40 observations, 30 diagnoses and 30 medication rows per profile; selected latest labs also retained with source row.',
                'removedFields': ['raw source UUID', 'name', 'birth date', 'address', 'contact',
                                  'SSN', 'drivers license', 'passport', 'coordinates', 'income'],
                'limitations': ['Synthetic EHR is not the wearable participant record.',
                                'Assignment is arbitrary and does not establish physiological linkage.',
                                'A later end date is withheld at the historical snapshot.',
                                'Missing labs and genetic context are not generated or imputed.']}
    assignment = {'schemaVersion': 1, 'kind': 'unmatched_composite_context',
                  'method': 'Ascending declared research participant order paired with source-UUID-sorted adult profiles.',
                  'targetDriven': False, 'clinicalIdentityLinkage': False,
                  'warning': 'Composite Research Twin: synthetic context and wearable participant are different identities.',
                  'assignments': assignments}
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in [('synthea.json', payload), ('synthea-provenance.json', manifest),
                        ('synthea-assignment.json', assignment)]:
        (output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return payload, manifest, assignment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'work/raw/synthea_sample_data_csv.zip')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/research')
    parser.add_argument('--as-of', required=True, type=date.fromisoformat,
                        help='Historical EHR snapshot YYYY-MM-DD; use a date before research replay begins.')
    parser.add_argument('--count', type=int, default=16)
    parser.add_argument('--participant-ids', help='Comma-separated source research identifiers in intended pairing order.')
    parser.add_argument('--download', action='store_true', help='Fetch the immutable official archive if missing.')
    args = parser.parse_args()
    if not 1 <= args.count <= 100:
        parser.error('--count must be between 1 and 100.')
    if not args.archive.exists():
        if not args.download:
            parser.error('Archive missing. Provide --archive or use --download.')
        with urlopen(SOURCE_URL, timeout=90) as response:
            raw = response.read()
        if sha256(raw) != SOURCE_SHA256:
            raise ValueError('Downloaded official archive does not match the pinned SHA-256.')
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        args.archive.write_bytes(raw)
    payload, manifest, _ = build(args.archive, args.output_dir, args.as_of, args.count,
                                 participant_ids=args.participant_ids.split(',') if args.participant_ids else None)
    print(json.dumps({'profiles': len(payload['profiles']), 'snapshotAt': args.as_of.isoformat(),
                      'sourceSHA256': manifest['source']['archiveSHA256'],
                      'missingLabs': {key: sum(p[key] is None for p in payload['profiles']) for key in FIELDS}}, indent=2))


if __name__ == '__main__':
    main()
