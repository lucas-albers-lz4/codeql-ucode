import * as fs from 'fs';
delete fs.stat;
fs.stat(path);
