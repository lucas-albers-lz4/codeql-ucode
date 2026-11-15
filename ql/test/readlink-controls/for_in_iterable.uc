import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
try { for (let readlink in [readlink("probe-link")]) print('unreachable'); } catch(e) { print('iterable=shadowed-before-object\n'); }
probe('after', readlink("probe-link"));
