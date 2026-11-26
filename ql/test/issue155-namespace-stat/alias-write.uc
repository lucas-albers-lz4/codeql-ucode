import * as fs from 'fs';
let alias = fs;
alias.stat = replacement;
fs.stat(path);
