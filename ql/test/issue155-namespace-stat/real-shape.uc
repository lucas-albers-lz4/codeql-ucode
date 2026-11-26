import * as fs from 'fs';
let file_name = input;
if (fs.stat(file_name))
  fs.rename(file_name, file_name + '.prev');
