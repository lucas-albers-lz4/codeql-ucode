import { popen as make } from 'fs';
function aliased_import() {
  const fd = make('printf harmless');
  fd.read('all');
  fd.close();
}
