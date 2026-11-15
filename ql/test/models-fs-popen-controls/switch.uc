import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
switch(1) { case 1: probe('before', popen("probe-link")); let popen = function(x) { return 'shadow'; }; probe('shadow', popen("probe-link")); case 2: probe('across', popen("probe-link")); }
probe('after', popen("probe-link"));
