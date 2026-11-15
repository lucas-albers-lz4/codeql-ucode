import { different as readlink } from 'other';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('alias', readlink("probe-link"));
