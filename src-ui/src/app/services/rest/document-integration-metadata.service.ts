import { HttpClient } from '@angular/common/http'
import { Injectable } from '@angular/core'
import { Observable } from 'rxjs'
import { environment } from 'src/environments/environment'
import {
  DocumentIntegrationMetadata,
  PushDocumentResult,
  SyncStatusResult,
} from '../../data/integration'
import { Results } from '../../data/results'

@Injectable({
  providedIn: 'root',
})
export class DocumentIntegrationMetadataService {
  private baseUrl = environment.apiBaseUrl + 'document_integration_metadata/'

  constructor(private http: HttpClient) {}

  /**
   * List all metadata entries
   */
  listAll(
    page?: number,
    pageSize?: number,
    sortField?: string,
    sortReverse?: boolean,
    filterParams?: any
  ): Observable<Results<DocumentIntegrationMetadata>> {
    let params: any = {}
    if (page) params.page = page
    if (pageSize) params.page_size = pageSize
    if (sortField) params.ordering = (sortReverse ? '-' : '') + sortField
    if (filterParams) params = { ...params, ...filterParams }

    return this.http.get<Results<DocumentIntegrationMetadata>>(
      this.baseUrl,
      { params }
    )
  }

  /**
   * Get metadata by ID
   */
  get(id: number): Observable<DocumentIntegrationMetadata> {
    return this.http.get<DocumentIntegrationMetadata>(`${this.baseUrl}${id}/`)
  }

  /**
   * Get metadata for a specific document and integration
   */
  getByDocumentAndIntegration(
    documentId: number,
    integrationId: number
  ): Observable<DocumentIntegrationMetadata> {
    return this.http.get<DocumentIntegrationMetadata>(this.baseUrl, {
      params: {
        document: documentId.toString(),
        integration: integrationId.toString(),
      },
    })
  }

  /**
   * Get all metadata for a specific document
   */
  getByDocument(documentId: number): Observable<Results<DocumentIntegrationMetadata>> {
    return this.http.get<Results<DocumentIntegrationMetadata>>(this.baseUrl, {
      params: {
        document: documentId.toString(),
      },
    })
  }

  /**
   * Create new metadata entry
   */
  create(
    metadata: DocumentIntegrationMetadata
  ): Observable<DocumentIntegrationMetadata> {
    return this.http.post<DocumentIntegrationMetadata>(this.baseUrl, metadata)
  }

  /**
   * Update existing metadata
   */
  update(
    metadata: DocumentIntegrationMetadata
  ): Observable<DocumentIntegrationMetadata> {
    return this.http.patch<DocumentIntegrationMetadata>(
      `${this.baseUrl}${metadata.id}/`,
      metadata
    )
  }

  /**
   * Delete metadata
   */
  delete(metadata: DocumentIntegrationMetadata): Observable<any> {
    return this.http.delete(`${this.baseUrl}${metadata.id}/`)
  }

  /**
   * Sync status from the external platform
   */
  syncStatus(metadataId: number): Observable<SyncStatusResult> {
    return this.http.post<SyncStatusResult>(
      `${this.baseUrl}${metadataId}/sync_status/`,
      {}
    )
  }
}
