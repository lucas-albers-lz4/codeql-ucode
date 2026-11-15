let prior=1;
function probe(label, value) { printf('%s=%s\n', label, value); }
import { readlink } from 'fs';
probe('late', readlink("probe-link"));
