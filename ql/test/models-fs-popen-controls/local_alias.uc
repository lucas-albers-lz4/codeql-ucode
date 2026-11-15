import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let rl=popen; probe('alias', rl("probe-link"));
