function probe(label, value) { printf('%s=%s\n', label, value); }
function early() { return popen("probe-link"); }
import { popen } from 'fs';
probe('early', early());
