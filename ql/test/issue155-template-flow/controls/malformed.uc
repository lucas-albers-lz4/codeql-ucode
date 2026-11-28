import { stat } from 'fs';
function handler(request) {
  return stat(`${request.args.service_name);
}
