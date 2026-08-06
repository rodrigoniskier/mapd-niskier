from django.urls import path
from . import views

urlpatterns = [
    path("", views.rotear_dashboard, name="rotear_dashboard"),
    path("entrar/", views.EntrarView.as_view(), name="login"),
    path("sair/", views.SairView.as_view(), name="logout"),
    path("primeiro-acesso/", views.primeiro_acesso, name="primeiro_acesso"),

    path("aluno/", views.aluno_dashboard, name="aluno_dashboard"),
    path("tema/<slug:slug>/", views.escolher_modo, name="escolher_modo"),
    path("tema/<slug:slug>/revisar/", views.revisar, name="revisar"),
    path("tema/<slug:slug>/avaliacao/iniciar/", views.iniciar_avaliacao, name="iniciar_avaliacao"),
    path("avaliacao/<int:pk>/", views.avaliacao, name="avaliacao"),
    path("avaliacao/<int:pk>/finalizar/", views.finalizar_avaliacao, name="finalizar_avaliacao"),
    path("avaliacao/<int:pk>/resultado/", views.resultado, name="resultado"),
    path("avaliacao/<int:pk>/feedback/", views.feedback, name="feedback"),
    path("tema/<slug:slug>/plantao/", views.plantao, name="plantao"),
    path("chat/<int:sessao_id>/enviar/", views.chat_enviar, name="chat_enviar"),

    path("professor/", views.professor_dashboard, name="professor_dashboard"),
    path("professor/tema/<int:tema_id>/gerar/", views.gerar_pacote, name="gerar_pacote"),
    path("professor/tema/<int:tema_id>/publicar/", views.publicar_pacote, name="publicar_pacote"),
    path("professor/tentativa/<int:tentativa_id>/nota/", views.ajustar_nota, name="ajustar_nota"),
]
