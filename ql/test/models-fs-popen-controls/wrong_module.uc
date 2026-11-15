import { popen } from 'other';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('wrong', popen("probe-link"));
