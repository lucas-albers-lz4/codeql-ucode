import { popen as rl } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('alias', rl("probe-link"));
