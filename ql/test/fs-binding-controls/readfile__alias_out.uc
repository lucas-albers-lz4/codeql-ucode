import { readfile as rf } from 'fs';
printf('native=%s\n', type(rf("fixtures/native.txt")));
