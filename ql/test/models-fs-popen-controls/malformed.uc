import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('parsed-prefix', popen("probe-link"));
let broken = ;
