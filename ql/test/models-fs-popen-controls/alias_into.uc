import { different as popen } from 'other';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('alias', popen("probe-link"));
