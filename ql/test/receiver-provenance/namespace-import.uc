import * as popen from 'fs';
function namespace_import() {
  const fd = popen('printf harmless');
  fd.read('all');
  fd.close();
}
