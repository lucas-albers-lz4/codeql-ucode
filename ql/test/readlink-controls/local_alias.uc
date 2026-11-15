import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let rl=readlink; probe('alias', rl("probe-link"));
