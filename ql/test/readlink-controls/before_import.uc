function probe(label, value) { printf('%s=%s\n', label, value); }
probe('early', readlink("probe-link"));
import { readlink } from 'fs';
