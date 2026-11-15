import * as fs from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('member', fs.popen("probe-link"));
