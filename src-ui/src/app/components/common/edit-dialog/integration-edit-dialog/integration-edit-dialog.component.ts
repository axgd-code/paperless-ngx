import { Component, inject } from '@angular/core'
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms'
import { EditDialogComponent } from 'src/app/components/common/edit-dialog/edit-dialog.component'
import { Integration, ProviderType } from 'src/app/data/integration'
import { IfOwnerDirective } from 'src/app/directives/if-owner.directive'
import { IntegrationService } from 'src/app/services/rest/integration.service'
import { UserService } from 'src/app/services/rest/user.service'
import { SettingsService } from 'src/app/services/settings.service'
import { CheckComponent } from '../../input/check/check.component'
import { PermissionsFormComponent } from '../../input/permissions/permissions-form/permissions-form.component'
import { SelectComponent } from '../../input/select/select.component'
import { TextComponent } from '../../input/text/text.component'
import { TextAreaComponent } from '../../input/textarea/textarea.component'

export const PROVIDER_TYPE_OPTIONS = [
  {
    id: ProviderType.Documenso,
    name: $localize`Documenso (Signature)`,
  },
  {
    id: ProviderType.Digiposte,
    name: $localize`Digiposte (Digital Vault)`,
  },
  {
    id: ProviderType.Custom,
    name: $localize`Custom Integration`,
  },
]

@Component({
  selector: 'pngx-integration-edit-dialog',
  templateUrl: './integration-edit-dialog.component.html',
  styleUrls: ['./integration-edit-dialog.component.scss'],
  imports: [
    CheckComponent,
    SelectComponent,
    PermissionsFormComponent,
    TextComponent,
    TextAreaComponent,
    IfOwnerDirective,
    FormsModule,
    ReactiveFormsModule,
  ],
})
export class IntegrationEditDialogComponent extends EditDialogComponent<Integration> {
  providerTypeOptions = PROVIDER_TYPE_OPTIONS

  // Field titles
  readonly titleName = $localize`Name`
  readonly titleProviderType = $localize`Provider Type`
  readonly titleApiUrl = $localize`API URL`
  readonly titleCredentials = $localize`Credentials (JSON)`
  readonly titleActive = $localize`Active`

  // Field hints
  readonly hintApiUrl = $localize`Base URL for the provider's API. Supports cloud (https://app.example.com) and local instances (http://localhost:3000)`
  readonly hintCredentials = $localize`JSON object with provider-specific credentials. Example: {"api_key": "your-key"}`
  readonly hintActive = $localize`Enable/disable this integration without deleting configuration`

  // Button labels
  readonly labelCancel = $localize`Cancel`
  readonly labelSave = $localize`Save`
  readonly labelClose = $localize`Close`

  constructor() {
    super()
    this.service = inject(IntegrationService)
    this.userService = inject(UserService)
    this.settingsService = inject(SettingsService)
  }

  getCreateTitle() {
    return $localize`Create new integration`
  }

  getEditTitle() {
    return $localize`Edit integration`
  }

  getForm(): FormGroup {
    return new FormGroup({
      name: new FormControl('', Validators.required),
      provider_type: new FormControl(ProviderType.Custom, Validators.required),
      api_url: new FormControl('', [Validators.required, this.urlValidator]),
      credentials: new FormControl(''),
      is_active: new FormControl(false),
      permissions_form: new FormControl(null),
    })
  }

  private urlValidator(control: FormControl): { [key: string]: any } | null {
    const value = control.value
    if (!value) return null

    try {
      const url = new URL(value)
      if (!['http:', 'https:'].includes(url.protocol)) {
        return { invalidUrl: { value } }
      }
      return null
    } catch {
      return { invalidUrl: { value } }
    }
  }

  protected override patchFormValue(object: Integration): void {
    super.patchFormValue(object)
    
    // Convert credentials object to JSON string for textarea
    if (object.credentials) {
      this.objectForm
        .get('credentials')
        .setValue(JSON.stringify(object.credentials, null, 2))
    }
  }

  protected override getUpdatedObject(): Integration {
    const formValue = super.getUpdatedObject()
    
    // Parse credentials JSON string back to object
    if (formValue.credentials && typeof formValue.credentials === 'string') {
      try {
        formValue.credentials = JSON.parse(formValue.credentials)
      } catch (e) {
        // Keep as string if parsing fails, backend will validate
      }
    }
    
    return formValue
  }
}
