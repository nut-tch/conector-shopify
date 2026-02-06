from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shopify_app", "0012_ordermapping"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="company",
            field=models.CharField(
                max_length=255,
                blank=True,
                verbose_name="Empresa",
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="nif",
            field=models.CharField(
                max_length=30,
                blank=True,
                verbose_name="NIF",
            ),
        ),
    ]

