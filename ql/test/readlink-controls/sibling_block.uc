import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ let readlink = function(x) { return 'shadow'; }; }
probe('sibling', readlink("probe-link"));
