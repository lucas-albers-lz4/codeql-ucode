import * as fs from 'fs';
function check(fs) {
  fs.stat(path);
  fs.rename(path, path + '.prev');
}
