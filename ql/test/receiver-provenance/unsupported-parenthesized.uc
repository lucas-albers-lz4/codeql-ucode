import { popen } from 'fs';
function unsupported_parenthesized() {
  const fd = popen('printf harmless');
  (fd.read)('all');
  fd.read('all');
}
