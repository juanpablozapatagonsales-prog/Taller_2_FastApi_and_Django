from django import forms


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = (
                "form-check-input"
                if isinstance(widget, forms.CheckboxInput)
                else "form-control"
            )
            widget.attrs["class"] = " ".join(
                filter(None, (widget.attrs.get("class", ""), css_class))
            )


class ProductForm(BootstrapFormMixin, forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "off", "minlength": "2"}),
    )
    descripcion = forms.CharField(
        label="Descripción",
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    precio = forms.DecimalField(
        label="Precio",
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )
    unidades = forms.IntegerField(
        label="Unidades",
        min_value=0,
        widget=forms.NumberInput(attrs={"min": "0", "step": "1"}),
    )
    imagen = forms.URLField(
        label="Imagen (enlace)",
        required=False,
        max_length=500,
        widget=forms.URLInput(
            attrs={"placeholder": "https://ejemplo.com/foto.jpg", "autocomplete": "off"}
        ),
    )
    activo = forms.BooleanField(label="Producto activo", required=False)

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen", "").strip()
        if imagen and not imagen.startswith(("http://", "https://")):
            raise forms.ValidationError("El enlace debe empezar con http:// o https://")
        return imagen


class PurchaseForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1)


class CustomerLoginForm(BootstrapFormMixin, forms.Form):
    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


AdminLoginForm = CustomerLoginForm


class CustomerSignupForm(BootstrapFormMixin, forms.Form):
    username = forms.RegexField(
        regex=r"^[\w.@+\-]+$",
        label="Usuario",
        min_length=3,
        max_length=50,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        min_length=8,
        max_length=72,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        min_length=8,
        max_length=72,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "minlength": "3",
            "maxlength": "50",
            "pattern": r"[\w.@+\-]+",
            "title": "Solo letras, números y @ . + - _",
        })
        self.fields["correo"].widget.attrs.update({
            "maxlength": "254",
            "placeholder": "correo@ejemplo.com",
        })
        self.fields["password1"].widget.attrs["minlength"] = "8"
        self.fields["password2"].widget.attrs["minlength"] = "8"

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las dos contraseñas no coinciden.")
        return cleaned_data
