import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function unrelated(readlink) { return readlink('unused'); }
probe('sibling', readlink("probe-link"));
