import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ let readlink = readlink("probe-link"); }
