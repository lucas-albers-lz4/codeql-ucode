function probe(label, value) { printf('%s=%s\n', label, value); }
function local() { import { readlink } from 'fs'; return readlink("probe-link"); }
probe('nested', local());
