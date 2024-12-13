from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.core.mail import send_mail
import mercadopago
from django.conf import settings

# MODELOS

class Paciente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.usuario.username

class Turno(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateField()
    hora = models.TimeField()
    disponible = models.BooleanField(default=True)
    pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"Turno {self.fecha} {self.hora} - {'Disponible' if self.disponible else 'Reservado'}"

class Mensaje(models.Model):
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensajes_enviados")
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensajes_recibidos")
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensaje de {self.remitente.username} a {self.destinatario.username}"

class Pago(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, default="Pendiente")

    def __str__(self):
        return f"Pago de {self.paciente.usuario.username} - {self.monto} - {self.estado}"

# VISTAS

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, "home.html")

@login_required
def reservar_turno(request):
    if request.method == "POST":
        turno_id = request.POST.get("turno_id")
        turno = Turno.objects.get(id=turno_id)
        if turno.disponible:
            turno.paciente = request.user.paciente
            turno.disponible = False
            turno.save()
            # Enviar notificación (opcional)
            send_mail(
                "Confirmación de Turno",
                f"Tu turno para la fecha {turno.fecha} a las {turno.hora} ha sido reservado.",
                "no-reply@turnero.com",
                [request.user.email]
            )
            return redirect("confirmar_pago", turno_id=turno.id)
    turnos = Turno.objects.filter(disponible=True)
    return render(request, "reservar_turno.html", {"turnos": turnos})

@login_required
def confirmar_pago(request, turno_id):
    turno = Turno.objects.get(id=turno_id)
    if not turno.paciente or turno.paciente != request.user.paciente:
        return redirect("home")

    mp = mercadopago.MP(settings.MERCADO_PAGO_ACCESS_TOKEN)
    preference_data = {
        "items": [
            {
                "title": f"Turno {turno.fecha} {turno.hora}",
                "quantity": 1,
                "unit_price": 1500.00,
                "currency_id": "ARS",
            }
        ],
        "back_urls": {
            "success": reverse("pago_exitoso", args=[turno.id]),
            "failure": reverse("pago_fallido", args=[turno.id]),
            "pending": reverse("pago_pendiente", args=[turno.id]),
        },
        "auto_return": "approved",
    }

    preference_response = mp.create_preference(preference_data)
    return redirect(preference_response["response"]["init_point"])

@login_required
def pago_exitoso(request, turno_id):
    turno = Turno.objects.get(id=turno_id)
    if turno.paciente and turno.paciente == request.user.paciente:
        turno.pagado = True
        turno.save()
    return render(request, "pago_exitoso.html")

@login_required
def cancelar_turno(request, turno_id):
    turno = Turno.objects.get(id=turno_id)
    if turno.paciente == request.user.paciente:
        turno.paciente = None
        turno.disponible = True
        turno.pagado = False
        turno.save()
        return redirect("home")
    return redirect("home")

# URLS

from django.urls import path

urlpatterns = [
    path("", home, name="home"),
    path("reservar/", reservar_turno, name="reservar_turno"),
    path("pago/<int:turno_id>/confirmar/", confirmar_pago, name="confirmar_pago"),
    path("pago/<int:turno_id>/exito/", pago_exitoso, name="pago_exitoso"),
    path("turno/<int:turno_id>/cancelar/", cancelar_turno, name="cancelar_turno"),
]

# PLANTILLAS

# Crear las siguientes plantillas HTML: home.html, reservar_turno.html, pago_exitoso.html.

# Este código puede ser mejorado y ampliado fácilmente con nuevas funcionalidades.
