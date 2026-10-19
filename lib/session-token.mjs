import {createCipheriv, createDecipheriv, randomBytes} from 'node:crypto';

const CONTEXT = Buffer.from('aura-twin/frozen-challenge/v1');

/** Carry an authenticated, encrypted snapshot across stateless function instances. */
export function createSessionCodec(hexKey) {
  if (typeof hexKey !== 'string' || !/^[0-9a-f]{64}$/i.test(hexKey)) {
    throw new TypeError('AURA_CHALLENGE_KEY must contain 32 random bytes encoded as 64 hexadecimal characters.');
  }
  const key = Buffer.from(hexKey, 'hex');
  return {
    seal(entry) {
      const iv = randomBytes(12);
      const cipher = createCipheriv('aes-256-gcm', key, iv);
      cipher.setAAD(CONTEXT);
      const encrypted = Buffer.concat([cipher.update(JSON.stringify(entry), 'utf8'), cipher.final()]);
      return ['v1', iv.toString('base64url'), encrypted.toString('base64url'), cipher.getAuthTag().toString('base64url')].join('.');
    },
    open(token) {
      if (typeof token !== 'string' || token.length > 100_000 || !/^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token)) {
        throw new TypeError('Invalid frozen challenge token.');
      }
      const [, ivText, ciphertext, tagText] = token.split('.');
      const iv = Buffer.from(ivText, 'base64url'), tag = Buffer.from(tagText, 'base64url');
      if (iv.length !== 12 || tag.length !== 16) throw new TypeError('Invalid frozen challenge token.');
      const decipher = createDecipheriv('aes-256-gcm', key, iv);
      decipher.setAAD(CONTEXT);
      decipher.setAuthTag(tag);
      const plaintext = Buffer.concat([decipher.update(Buffer.from(ciphertext, 'base64url')), decipher.final()]);
      return JSON.parse(plaintext.toString('utf8'));
    },
  };
}
