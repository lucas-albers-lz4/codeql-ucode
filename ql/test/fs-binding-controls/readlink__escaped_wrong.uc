import { readlink } from 'f\x2fs';
printf('wrong=%s\n', readlink("fixtures/native-link"));
