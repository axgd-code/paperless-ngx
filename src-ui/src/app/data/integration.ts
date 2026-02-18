import { ObjectWithPermissions } from './object-with-permissions'

export enum ProviderType {
  Documenso = 1,
  Digiposte = 2,
  Custom = 99,
}

export interface Integration extends ObjectWithPermissions {
  name: string
  provider_type: ProviderType
  api_url: string
  credentials?: {
    api_key?: string
    username?: string
    password?: string
    access_token?: string
    refresh_token?: string
    client_id?: string
    client_secret?: string
    expires_at?: string
  }
  is_active: boolean
  created?: string // ISO date string
  modified?: string // ISO date string
}


/**
 * Status values for documents on external integration platforms
 */
export enum IntegrationStatus {
  Pending = 'pending',
  Processing = 'processing',
  Completed = 'completed',
  Signed = 'signed',
  Archived = 'archived',
  Failed = 'failed',
  Rejected = 'rejected',
  Expired = 'expired',
}


/**
 * Metadata tracking a document's status on an external integration
 */
export interface DocumentIntegrationMetadata {
  id?: number
  document: number
  document_title?: string
  integration: number
  integration_name?: string
  provider_type?: ProviderType
  remote_id: string
  status: string
  remote_url?: string
  metadata?: any
  created?: string
  updated?: string
  last_synced?: string
}


/**
 * Generic interface for integration provider actions
 * This interface allows the UI to dynamically show/hide actions
 * based on what each provider supports
 */
export interface IntegrationProviderCapabilities {
  /**
   * Can this provider push documents?
   */
  canPush: boolean
  
  /**
   * Can this provider retrieve status?
   */
  canGetStatus: boolean
  
  /**
   * Can this provider provide a remote URL?
   */
  canGetRemoteUrl: boolean
  
  /**
   * Can this provider delete remote documents?
   */
  canDelete: boolean
  
  /**
   * Display name for push action (e.g., "Send for Signature", "Archive to Vault")
   */
  pushActionLabel?: string
  
  /**
   * Display name for status action (e.g., "Check Signature Status", "View Archive Status")
   */
  statusActionLabel?: string
  
  /**
   * Icon name for this provider (from Bootstrap Icons)
   */
  iconName?: string
}


/**
 * Result of pushing a document to a provider
 */
export interface PushDocumentResult {
  success: boolean
  document_id: number
  integration_id: number
  remote_id?: string
  remote_url?: string
  status?: string
  message?: string
}


/**
 * Result of syncing status from a provider
 */
export interface SyncStatusResult {
  success: boolean
  metadata_id: number
  status?: string
  updated_at?: string
  message?: string
}


/**
 * Provider registry mapping provider types to their capabilities
 */
export const PROVIDER_CAPABILITIES: Record<ProviderType, IntegrationProviderCapabilities> = {
  [ProviderType.Documenso]: {
    canPush: true,
    canGetStatus: true,
    canGetRemoteUrl: true,
    canDelete: false,
    pushActionLabel: $localize`Send for Signature`,
    statusActionLabel: $localize`Check Signature Status`,
    iconName: 'pen',
  },
  [ProviderType.Digiposte]: {
    canPush: true,
    canGetStatus: true,
    canGetRemoteUrl: true,
    canDelete: true,
    pushActionLabel: $localize`Archive to Vault`,
    statusActionLabel: $localize`Check Archive Status`,
    iconName: 'safe',
  },
  [ProviderType.Custom]: {
    canPush: true,
    canGetStatus: false,
    canGetRemoteUrl: false,
    canDelete: false,
    pushActionLabel: $localize`Send to Integration`,
    statusActionLabel: $localize`Check Status`,
    iconName: 'plugin',
  },
}


/**
 * Get the capabilities for a specific provider type
 */
export function getProviderCapabilities(providerType: ProviderType): IntegrationProviderCapabilities {
  return PROVIDER_CAPABILITIES[providerType] || PROVIDER_CAPABILITIES[ProviderType.Custom]
}


/**
 * Get a human-readable status label for an integration status
 */
export function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    [IntegrationStatus.Pending]: $localize`Pending`,
    [IntegrationStatus.Processing]: $localize`Processing`,
    [IntegrationStatus.Completed]: $localize`Completed`,
    [IntegrationStatus.Signed]: $localize`Signed`,
    [IntegrationStatus.Archived]: $localize`Archived`,
    [IntegrationStatus.Failed]: $localize`Failed`,
    [IntegrationStatus.Rejected]: $localize`Rejected`,
    [IntegrationStatus.Expired]: $localize`Expired`,
  }
  return statusMap[status] || status
}


/**
 * Get a badge class for an integration status
 */
export function getStatusBadgeClass(status: string): string {
  const classMap: Record<string, string> = {
    [IntegrationStatus.Pending]: 'bg-warning',
    [IntegrationStatus.Processing]: 'bg-info',
    [IntegrationStatus.Completed]: 'bg-success',
    [IntegrationStatus.Signed]: 'bg-success',
    [IntegrationStatus.Archived]: 'bg-primary',
    [IntegrationStatus.Failed]: 'bg-danger',
    [IntegrationStatus.Rejected]: 'bg-danger',
    [IntegrationStatus.Expired]: 'bg-secondary',
  }
  return classMap[status] || 'bg-secondary'
}
