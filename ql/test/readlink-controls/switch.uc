import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
switch(1) { case 1: probe('before', readlink("probe-link")); let readlink = function(x) { return 'shadow'; }; probe('shadow', readlink("probe-link")); case 2: probe('across', readlink("probe-link")); }
probe('after', readlink("probe-link"));
