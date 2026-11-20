import { popen } from 'fs';
function shorthand_escape() {
  const fd = popen('printf harmless');
  const bundle = { fd };
  fd.read('all');
  fd.close();
  return bundle;
}
