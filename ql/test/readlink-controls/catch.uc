import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
try { die('test'); } catch(readlink) { try { readlink("probe-link"); } catch(e) { print('catch=not-callable\n'); } }
probe('after', readlink("probe-link"));
