import {createAppHandler} from '../server.mjs';

// Every instance must use the same deployment secret. Fail closed instead of
// falling back to memory and losing challenges on the next invocation.
if (!process.env.AURA_CHALLENGE_KEY) throw new Error('AURA_CHALLENGE_KEY is required for the hosted Challenge Lab.');
const handler = createAppHandler({sessionKey: process.env.AURA_CHALLENGE_KEY, allowExternalPatients: false});
export default handler;
