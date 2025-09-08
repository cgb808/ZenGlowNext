import dotenv from 'dotenv';

dotenv.config();

const requiredVariables = ['SUPABASE_URL', 'SERVICE_ROLE_KEY', 'PORT'];

const missingVariables = requiredVariables.filter((key) => !process.env[key]);

if (missingVariables.length > 0) {
  console.error('The following required environment variables are missing:', missingVariables);
  process.exit(1);
} else {
  console.log('All required environment variables are set.');
}
