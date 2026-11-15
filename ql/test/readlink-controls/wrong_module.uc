import { readlink } from 'other';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('wrong', readlink("probe-link"));
