import { stat, rename } from 'fs';
stat(path);
rename(path, path + '.prev');
