function probe(label, value) { printf('%s=%s\n', label, value); }
probe('early', popen("probe-link"));
import { popen } from 'fs';
