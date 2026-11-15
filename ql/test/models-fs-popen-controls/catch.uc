import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
try { die('test'); } catch(popen) { try { popen("probe-link"); } catch(e) { print('catch=not-callable\n'); } }
probe('after', popen("probe-link"));
