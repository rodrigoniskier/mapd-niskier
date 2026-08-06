from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AlterModelOptions(
            name="usuario",
            options={"verbose_name": "usuário", "verbose_name_plural": "usuários"},
        ),
    ]
