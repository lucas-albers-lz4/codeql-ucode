function probe(label, value) { printf('%s=%s\n', label, value); }
function early() { return readlink("probe-link"); }
import { readlink } from 'fs';
probe('early', early());
