import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
switch(1) { case 1: probe('switch', readlink("probe-link")); }
probe('after', readlink("probe-link"));
