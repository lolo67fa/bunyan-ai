// The only module screens import. Switch with VITE_API_MODE=mock|http in .env.local.
import * as mock from './mockServer.js';
import * as http from './httpClient.js';

const api = import.meta.env.VITE_API_MODE === 'http' ? http : mock;

export const {
  createProject,
  getProject,
  submitAnswers,
  approveRequirements,
  getArtifactText,
  getPreviewHtml,
  previewUrl,
  downloadUrl,
  MODE,
} = api;
