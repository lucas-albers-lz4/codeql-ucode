import { readlink } from 'fs';
import { different as readlink } from 'other';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('duplicate', readlink("probe-link"));
