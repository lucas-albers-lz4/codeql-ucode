import { readlink } from 'fs';
printf('native=%s\n', type(readlink("fixtures/native-link")));
