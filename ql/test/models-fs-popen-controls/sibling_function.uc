import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function unrelated(popen) { return popen('unused'); }
probe('sibling', popen("probe-link"));
