from PIL import Image, ImageOps
import os
from datetime import datetime
import time
import subprocess
import platform
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
import pikepdf

console = Console()


def print_header():
    console.print(Panel.fit(
        "[bold cyan]IMAGE & PDF PROCESSOR[/bold cyan]\n"
        "[dim]Фото + PDF • Конвертация • Сжатие[/dim]",
        border_style="bright_blue",
        padding=(1, 2)
    ))


def print_menu():
    console.print("\n[bold]Выбери действие:[/bold]")
    console.print("  [green]1.[/green] Конвертировать формат фото")
    console.print("  [green]2.[/green] Сжать фото")
    console.print("  [green]3.[/green] Конвертировать + Сжать фото")
    console.print("  [yellow]4.[/yellow] Сжать PDF файлы")
    console.print("  [red]5.[/red] Выход\n")


def open_folder(path):
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        console.print(f"[yellow]Не удалось открыть папку: {e}[/yellow]")


def get_output_folder(prefix="processed"):
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")
    folder_name = f"{prefix}_{now}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} GB"


def get_folder_size(folder_path):
    total = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total


def process_images(mode):
    start_time = time.time()
    output_dir = get_output_folder("processed")

    # Выбор формата
    output_format = None
    extension = None
    if mode in [1, 3]:
        console.print("[bold]Выбери формат сохранения:[/bold]")
        console.print("  [cyan]1.[/cyan] PNG    [cyan]2.[/cyan] JPEG    [cyan]3.[/cyan] WebP")
        choice = console.input("[bold]Номер: [/bold]").strip()

        if choice == "1":
            output_format, extension = "PNG", ".png"
        elif choice == "2":
            output_format, extension = "JPEG", ".jpg"
        elif choice == "3":
            output_format, extension = "WEBP", ".webp"
        else:
            output_format, extension = "PNG", ".png"

    # Настройки сжатия
    max_size = None
    quality = 75

    if mode in [2, 3]:
        try:
            max_size = int(console.input("[bold]Макс. размер длинной стороны[/bold] [dim](1920)[/dim]: ") or 1920)
            quality = int(console.input("[bold]Качество (1-100)[/bold] [dim](75)[/dim]: ") or 75)
        except:
            max_size, quality = 1920, 75

    # Поиск файлов
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    files = [f for f in os.listdir(os.getcwd()) if f.lower().endswith(image_extensions)]

    if not files:
        console.print("[red]В текущей папке нет изображений![/red]")
        return

    original_size = sum(os.path.getsize(f) for f in files)
    console.print(f"\n[bold]Найдено файлов:[/bold] {len(files)}")
    console.print(f"[bold]Исходный размер:[/bold] {format_size(original_size)}\n")

    processed = 0

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Обработка изображений...", total=len(files))

        for filename in files:
            input_path = os.path.join(os.getcwd(), filename)
            name = os.path.splitext(filename)[0]
            out_ext = extension if output_format else os.path.splitext(filename)[1].lower()
            output_path = os.path.join(output_dir, f"{name}{out_ext}")

            try:
                with Image.open(input_path) as img:
                    original_w, original_h = img.width, img.height
                    img = ImageOps.exif_transpose(img)

                    # Изменение размера
                    if max_size:
                        ratio = max_size / max(img.width, img.height)
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)

                    # Сохранение
                    if output_format == "JPEG":
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.save(output_path, "JPEG", quality=quality, optimize=True)
                    elif output_format == "PNG":
                        img.save(output_path, "PNG", optimize=True)
                    elif output_format == "WEBP":
                        img.save(output_path, "WEBP", quality=quality, method=6)
                    else:
                        img.save(output_path)

                    processed += 1
                    progress.update(task, advance=1, 
                                    description=f"[green]✓[/green] {filename} ({original_w}x{original_h} → {img.width}x{img.height})")

            except Exception:
                progress.update(task, advance=1, description=f"[red]✗[/red] {filename}")

    # Статистика
    elapsed = time.time() - start_time
    new_size = get_folder_size(output_dir)
    saved = original_size - new_size
    percent = (saved / original_size * 100) if original_size > 0 else 0

    console.print(f"\n[bold green]Готово![/bold green]")
    console.print(f"Обработано: [bold]{processed}[/bold] файл(ов)")
    console.print(f"Время: {elapsed:.2f} сек")
    console.print(f"Исходный размер: [yellow]{format_size(original_size)}[/yellow]")
    console.print(f"Новый размер:    [green]{format_size(new_size)}[/green]")
    console.print(f"Сэкономлено:     [bold green]{format_size(saved)}[/bold green] ([bold green]{percent:.1f}%[/bold green])")
    console.print(f"Папка: [cyan]{output_dir}[/cyan]\n")

    open_folder(output_dir)


def compress_pdf():
    start_time = time.time()
    output_dir = get_output_folder("compressed_pdf")

    pdf_files = [f for f in os.listdir(os.getcwd()) if f.lower().endswith('.pdf')]

    if not pdf_files:
        console.print("[red]PDF файлов не найдено в папке![/red]")
        return

    console.print(f"\n[bold]Найдено PDF файлов:[/bold] {len(pdf_files)}")
    original_size = sum(os.path.getsize(f) for f in pdf_files)

    compressed = 0
    with Progress(console=console) as progress:
        task = progress.add_task("[yellow]Сжатие PDF...", total=len(pdf_files))

        for filename in pdf_files:
            input_path = os.path.join(os.getcwd(), filename)
            output_path = os.path.join(output_dir, filename)
            try:
                with pikepdf.open(input_path) as pdf:
                    pdf.save(output_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
                compressed += 1
                progress.update(task, advance=1, description=f"[green]✓[/green] {filename}")
            except Exception:
                progress.update(task, advance=1, description=f"[red]✗[/red] {filename}")

    new_size = get_folder_size(output_dir)
    saved = original_size - new_size
    percent = (saved / original_size * 100) if original_size > 0 else 0
    elapsed = time.time() - start_time

    console.print(f"\n[bold green]Готово![/bold green]")
    console.print(f"Сжато PDF: [bold]{compressed}[/bold]")
    console.print(f"Время: {elapsed:.2f} сек")
    console.print(f"Сэкономлено: [bold green]{format_size(saved)}[/bold green] ([bold green]{percent:.1f}%[/bold green])")
    console.print(f"Папка: [cyan]{output_dir}[/cyan]\n")

    open_folder(output_dir)


def main():
    while True:
        print_header()
        print_menu()

        choice = console.input("[bold]Выбери пункт: [/bold]").strip()

        if choice == "1":
            process_images(1)
        elif choice == "2":
            process_images(2)
        elif choice == "3":
            process_images(3)
        elif choice == "4":
            compress_pdf()
        elif choice == "5":
            console.print("\n[bold red]Выход из программы.[/bold red]")
            break
        else:
            console.print("[red]Неверный выбор![/red]")

        console.input("\n[dim]Нажми Enter, чтобы вернуться в меню...[/dim]")


if __name__ == "__main__":
    main()