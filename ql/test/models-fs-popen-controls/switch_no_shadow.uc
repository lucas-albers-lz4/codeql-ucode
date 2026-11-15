import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
switch(1) { case 1: probe('switch', popen("probe-link")); }
probe('after', popen("probe-link"));
