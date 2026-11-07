// Copies the Business Analyst sample outputs into the frontend mocks so the
// mock API always uses Ghala's real requirements.json samples.
// Run after the analyst contract changes:  npm run sync-samples
import { copyFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, '../../backend/agents/business_analyst/samples/outputs');
const dest = join(here, '../src/mocks/requirements');

if (!existsSync(src)) {
  console.error(`Samples folder not found: ${src}`);
  console.error('Merge or check out the Business Analyst branch first (PR #2).');
  process.exit(1);
}
mkdirSync(dest, { recursive: true });
const files = readdirSync(src).filter((f) => f.endsWith('.requirements.json'));
for (const f of files) copyFileSync(join(src, f), join(dest, f));
console.log(`Copied ${files.length} sample(s) into src/mocks/requirements/`);
