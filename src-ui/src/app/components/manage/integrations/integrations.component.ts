import { Component, OnInit, inject } from '@angular/core'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { NgbDropdownModule, NgbModal } from '@ng-bootstrap/ng-bootstrap'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { delay, takeUntil, tap } from 'rxjs'
import { Integration, ProviderType } from 'src/app/data/integration'
import { IfPermissionsDirective } from 'src/app/directives/if-permissions.directive'
import { PermissionsService } from 'src/app/services/permissions.service'
import { IntegrationService } from 'src/app/services/rest/integration.service'
import { ToastService } from 'src/app/services/toast.service'
import { ConfirmDialogComponent } from '../../common/confirm-dialog/confirm-dialog.component'
import { EditDialogMode } from '../../common/edit-dialog/edit-dialog.component'
import { IntegrationEditDialogComponent } from '../../common/edit-dialog/integration-edit-dialog/integration-edit-dialog.component'
import { PageHeaderComponent } from '../../common/page-header/page-header.component'
import { LoadingComponentWithPermissions } from '../../loading-component/loading.component'

@Component({
  selector: 'pngx-integrations',
  templateUrl: './integrations.component.html',
  styleUrls: ['./integrations.component.scss'],
  imports: [
    PageHeaderComponent,
    IfPermissionsDirective,
    FormsModule,
    ReactiveFormsModule,
    NgbDropdownModule,
    NgxBootstrapIconsModule,
  ],
})
export class IntegrationsComponent
  extends LoadingComponentWithPermissions
  implements OnInit
{
  private integrationService = inject(IntegrationService)
  permissionsService = inject(PermissionsService)
  private modalService = inject(NgbModal)
  private toastService = inject(ToastService)

  public integrations: Integration[] = []
  public ProviderType = ProviderType

  ngOnInit() {
    this.reload()
  }

  reload() {
    this.loading = true
    this.integrationService
      .listAll()
      .pipe(
        takeUntil(this.unsubscribeNotifier),
        tap((r) => (this.integrations = r.results)),
        delay(100)
      )
      .subscribe(() => {
        this.show = true
        this.loading = false
      })
  }

  getProviderTypeName(providerType: ProviderType): string {
    switch (providerType) {
      case ProviderType.Documenso:
        return $localize`Documenso (Signature)`
      case ProviderType.Digiposte:
        return $localize`Digiposte (Digital Vault)`
      case ProviderType.Custom:
        return $localize`Custom Integration`
      default:
        return $localize`Unknown`
    }
  }

  editIntegration(integration?: Integration) {
    const modal = this.modalService.open(IntegrationEditDialogComponent, {
      backdrop: 'static',
      size: 'xl',
    })
    modal.componentInstance.dialogMode = integration
      ? EditDialogMode.EDIT
      : EditDialogMode.CREATE
    if (integration) {
      modal.componentInstance.object = Object.assign({}, integration)
    }
    modal.componentInstance.succeeded
      .pipe(takeUntil(this.unsubscribeNotifier))
      .subscribe(() => {
        this.reload()
      })
  }

  toggleActive(integration: Integration) {
    integration.is_active = !integration.is_active
    this.integrationService.update(integration).subscribe({
      next: () => {
        this.toastService.showInfo(
          $localize`Integration "${integration.name}" ${
            integration.is_active ? 'activated' : 'deactivated'
          }`
        )
        this.reload()
      },
      error: (error) => {
        this.toastService.showError(
          $localize`Error updating integration`,
          error
        )
        integration.is_active = !integration.is_active
      },
    })
  }

  testConnection(integration: Integration) {
    this.integrationService.testConnection(integration).subscribe({
      next: (result) => {
        this.toastService.showInfo(
          $localize`Connection test successful for "${integration.name}"`
        )
      },
      error: (error) => {
        this.toastService.showError(
          $localize`Connection test failed for "${integration.name}"`,
          error
        )
      },
    })
  }

  deleteIntegration(integration: Integration) {
    const modal = this.modalService.open(ConfirmDialogComponent, {
      backdrop: 'static',
    })
    modal.componentInstance.title = $localize`Confirm delete integration`
    modal.componentInstance.messageBold = $localize`This operation will permanently delete this integration.`
    modal.componentInstance.message = $localize`This operation cannot be undone.`
    modal.componentInstance.btnClass = 'btn-danger'
    modal.componentInstance.btnCaption = $localize`Delete integration`
    modal.componentInstance.confirmClicked.subscribe(() => {
      modal.componentInstance.buttonsEnabled = false
      this.integrationService.delete(integration).subscribe({
        next: () => {
          modal.close()
          this.toastService.showInfo(
            $localize`Integration "${integration.name}" deleted`
          )
          this.reload()
        },
        error: (error) => {
          this.toastService.showError(
            $localize`Error deleting integration`,
            error
          )
          modal.componentInstance.buttonsEnabled = true
        },
      })
    })
  }
}
