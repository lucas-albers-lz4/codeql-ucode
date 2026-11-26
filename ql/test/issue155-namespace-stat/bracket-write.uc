import * as fs from 'fs';
fs['stat'] = replacement;
fs.stat(path);
