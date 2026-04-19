#!/usr/bin/env node
/**
 * Bucket initialization script for both MinIO and GCS.
 * 
 * This script ensures that the required bucket exists for the configured storage backend.
 * It should be run during application initialization or deployment setup.
 * 
 * Usage:
 *     node scripts/initialize-bucket.ts
 * 
 * Environment Variables:
 *     STORAGE_BACKEND: 'minio' or 'gcs' (default: 'minio')
 *     OBJECT_STORE_BUCKET: Bucket name (default: 'vhl' for MinIO, 'vhl-storage' for GCS)
 *     
 *     MinIO specific:
 *         MINIO_ENDPOINT: MinIO endpoint URL (default: 'http://minio:9000')
 *         MINIO_ROOT_USER: MinIO root username (default: 'minioadmin')
 *         MINIO_ROOT_PASSWORD: MinIO root password (default: 'supersecretpassword')
 *     
 *     GCS specific:
 *         GCP_PROJECT: GCP project ID
 */

import * as Minio from 'minio';
import { Storage } from '@google-cloud/storage';

const logger = {
  info: (msg: string) => console.log(`[INFO] ${new Date().toISOString()} - ${msg}`),
  error: (msg: string) => console.error(`[ERROR] ${new Date().toISOString()} - ${msg}`),
  warn: (msg: string) => console.warn(`[WARN] ${new Date().toISOString()} - ${msg}`),
};

async function initializeMinIOBucket(): Promise<boolean> {
  const bucketName = process.env.OBJECT_STORE_BUCKET || 'vhl';
  const endpoint = process.env.MINIO_ENDPOINT || 'minio';
  const port = process.env.MINIO_PORT ? parseInt(process.env.MINIO_PORT) : 9000;
  const accessKey = process.env.MINIO_ROOT_USER || 'minioadmin';
  const secretKey = process.env.MINIO_ROOT_PASSWORD || 'supersecretpassword';
  const useSSL = process.env.MINIO_USE_SSL === 'true';

  try {
    logger.info(`Connecting to MinIO at ${endpoint}:${port}...`);
    const client = new Minio.Client({
      endPoint: endpoint,
      port,
      accessKey,
      secretKey,
      useSSL,
    });

    // Check if bucket exists
    const exists = await client.bucketExists(bucketName);
    
    if (exists) {
      logger.info(`✓ MinIO bucket '${bucketName}' already exists`);
      return true;
    } else {
      logger.info(`Creating MinIO bucket '${bucketName}'...`);
      await client.makeBucket(bucketName, 'us-east-1');
      logger.info(`✓ Created MinIO bucket '${bucketName}'`);
      return true;
    }
  } catch (error) {
    logger.error(`✗ Failed to initialize MinIO bucket: ${error}`);
    return false;
  }
}

async function initializeGCSBucket(): Promise<boolean> {
  const bucketName = process.env.OBJECT_STORE_BUCKET || 'vhl-storage';
  const gcpProject = process.env.GCP_PROJECT;

  if (!gcpProject) {
    logger.warn('GCP_PROJECT not set. Attempting to use application default credentials...');
  }

  try {
    logger.info(`Connecting to GCS project '${gcpProject}'...`);
    const storage = new Storage({ projectId: gcpProject });
    const bucket = storage.bucket(bucketName);

    const [exists] = await bucket.exists();

    if (exists) {
      logger.info(`✓ GCS bucket '${bucketName}' already exists`);
      return true;
    } else {
      logger.info(`Creating GCS bucket '${bucketName}'...`);
      await storage.createBucket(bucketName, {
        location: 'US',
      });
      logger.info(`✓ Created GCS bucket '${bucketName}'`);
      return true;
    }
  } catch (error) {
    logger.error(`✗ Failed to initialize GCS bucket: ${error}`);
    return false;
  }
}

async function main(): Promise<number> {
  const backend = (process.env.STORAGE_BACKEND || 'minio').toLowerCase();

  logger.info(`Initializing storage backend: ${backend}`);

  let success: boolean;

  if (backend === 'minio') {
    success = await initializeMinIOBucket();
  } else if (backend === 'gcs') {
    success = await initializeGCSBucket();
  } else {
    logger.error(`✗ Unknown storage backend: ${backend}`);
    return 1;
  }

  if (success) {
    logger.info('✓ Bucket initialization successful');
    return 0;
  } else {
    logger.error('✗ Bucket initialization failed');
    return 1;
  }
}

main()
  .then((exitCode) => process.exit(exitCode))
  .catch((error) => {
    logger.error(`Unexpected error: ${error}`);
    process.exit(1);
  });
