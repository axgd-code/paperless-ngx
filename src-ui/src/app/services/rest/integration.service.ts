import { HttpClient } from '@angular/common/http'
import { Injectable } from '@angular/core'
import { Observable } from 'rxjs'
import { tap } from 'rxjs/operators'
import { Integration } from 'src/app/data/integration'
import { AbstractPaperlessService } from './abstract-paperless-service'

@Injectable({
  providedIn: 'root',
})
export class IntegrationService extends AbstractPaperlessService<Integration> {
  private integrations: Integration[] = []

  constructor() {
    super()
    this.resourceName = 'integrations'
  }

  public reload() {
    this._loading = true
    this.listAll().subscribe((r) => {
      this.integrations = r.results
      this._loading = false
    })
  }

  public get allIntegrations(): Integration[] {
    return this.integrations
  }

  public get activeIntegrations(): Integration[] {
    return this.integrations.filter((i) => i.is_active)
  }

  create(o: Integration) {
    return super.create(o).pipe(tap(() => this.reload()))
  }

  update(o: Integration) {
    return super.update(o).pipe(tap(() => this.reload()))
  }

  delete(o: Integration) {
    return super.delete(o).pipe(tap(() => this.reload()))
  }

  /**
   * Test connection to an integration provider
   */
  testConnection(integration: Integration): Observable<any> {
    return this.http.post(
      this.getResourceUrl(integration.id, 'test_connection'),
      {}
    )
  }

  /**
   * Send a document to an integration provider
   */
  sendDocument(
    documentId: number,
    integrationId: number
  ): Observable<any> {
    return this.http.post(
      `${this.baseUrl}integrations/${integrationId}/send_document/`,
      { document_id: documentId }
    )
  }

  /**
   * Send multiple documents to an integration provider (bulk action)
   */
  sendDocumentsBulk(
    documentIds: number[],
    integrationId: number
  ): Observable<any> {
    return this.http.post(
      `${this.baseUrl}integrations/${integrationId}/send_documents_bulk/`,
      { document_ids: documentIds }
    )
  }
}
